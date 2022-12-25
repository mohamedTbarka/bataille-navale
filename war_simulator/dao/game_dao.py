from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, relationship

from war_simulator.model.battlefield import Battlefield
from war_simulator.model.game import Game
from war_simulator.model.player import Player
import sqlalchemy.types as types

from war_simulator.model.vessel import Vessel

engine = create_engine('sqlite:////tmp/td---------log.db', echo=True, future=True)
Base = declarative_base(bind=engine)
Session = sessionmaker(bind=engine)


class GameEntity(Base):
    __tablename__ = 'game'
    id = Column(Integer, primary_key=True)
    players = relationship("PlayerEntity", back_populates="game", cascade="all, delete-orphan")


class PlayerEntity(Base):
    __tablename__ = 'player'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    game_id = Column(Integer, ForeignKey("game.id"), nullable=False)
    game = relationship("GameEntity", back_populates="players")
    battle_fields = relationship("BattlefieldEntity", back_populates="player", uselist=False,
                                 cascade="all, delete-orphan")


class BattlefieldEntity(Base):
    __tablename__ = 'battlefield'
    id = Column(Integer, primary_key=True)
    min_x = Column(Integer, nullable=False)
    min_y = Column(Integer, nullable=False)
    min_z = Column(Integer, nullable=False)
    max_x = Column(Integer, nullable=False)
    max_y = Column(Integer, nullable=False)
    max_z = Column(Integer, nullable=False)
    max_power = Column(Integer, nullable=False)
    player_id = Column(Integer, ForeignKey("player.id"), nullable=False)
    player = relationship("PlayerEntity", back_populates="battle_fields", )
    vessels = relationship("VesselEntity", back_populates="battlefield", cascade="all, delete-orphan")


class ChoiceType(types.TypeDecorator):
    impl = types.String

    def __init__(self, choices, **kw):
        self.choices = dict(choices)
        super(ChoiceType, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        return [k for k, v in self.choices.iteritems() if v == value][0]

    def process_result_value(self, value, dialect):
        return self.choices[value]


class Entity(Base):
    __tablename__ = "entity"
    id = Column(Integer, primary_key=True)
    height = Column(ChoiceType({"short": "short", "medium": "medium", "tall": "tall"}), nullable=False)


class VesselEntity(Base):
    CRUISER = "Cruiser"
    DESTROYER = "Destroyer"
    FRIGATE = "Frigate"
    SUBMARINE = "Submarine"

    __tablename__ = 'vessel'
    id = Column(Integer, primary_key=True)
    coord_x = Column(Integer, nullable=False)
    coord_y = Column(Integer, nullable=False)
    coord_z = Column(Integer, nullable=False)
    hits_to_be_destroyed = Column(Integer, nullable=False)
    battle_id = Column(Integer, ForeignKey("battlefield.id"), nullable=False)

    battlefield = relationship("BattlefieldEntity", back_populates="vessels")
    type = Column(ChoiceType({CRUISER: CRUISER, DESTROYER: DESTROYER, FRIGATE: FRIGATE, SUBMARINE: SUBMARINE}),
                  nullable=False)
    weapons = relationship("WeaponEntity", back_populates="vessel", cascade="all, delete-orphan")


class WeaponEntity(Base):
    AIRMISSILELAUNCHER = "AirMissileLauncher"
    SURFACEMISSILELAUNCHER = "SurfaceMissileLauncher"
    TORPEDOLAUNCHER = "TorpedoLauncher"

    __tablename__ = 'weapon'
    id = Column(Integer, primary_key=True)
    ammunitions = Column(Integer, nullable=False)
    range = Column(Integer, nullable=False)
    vessel_id = Column(Integer, ForeignKey("vessel.id"), nullable=False)
    vessel = relationship("VesselEntity", back_populates="weapons")
    type = Column(ChoiceType({AIRMISSILELAUNCHER: AIRMISSILELAUNCHER, SURFACEMISSILELAUNCHER: SURFACEMISSILELAUNCHER,
                              TORPEDOLAUNCHER: TORPEDOLAUNCHER}), nullable=False)


def map_to_game_entity(game: Game):
    return GameEntity(id=game.id)


def map_to_game(game_entity: GameEntity):
    g = Game(id=game_entity.id)
    for player in game_entity.players:
        g.add_player(player)
    return g


def map_to_battle_field_entity(battlefield: Battlefield):
    return BattlefieldEntity(battlefield.min_x, battlefield.min_y, battlefield.min_z, battlefield.max_x,
                             battlefield.max_y, battlefield.max_z, battlefield.max_power, )


def map_to_player_entity(player: Player, game: Game):
    return PlayerEntity(id=player.id, name=player.name, game_id=game.id, game=map_to_game_entity(game))


def map_to_vessel_entity(vessel: Vessel, battlefield: Battlefield):
    coord_x, coord_y, coord_z = vessel.get_coordinates()
    return VesselEntity(id=vessel.id, coord_x=coord_x, coord_y=coord_y, coord_z=coord_z,
                        hits_to_be_destroyed=vessel.hits_to_be_destroyed,
                        battlefield=map_to_battle_field_entity(battlefield), type=vessel)


class BattleField:
    pass


class GameDao:
    def __init__(self):
        Base.metadata.create_all()
        self.db_session = Session()

    def create_game(self, game: Game) -> int:
        game_entity = map_to_game_entity(game)
        self.db_session.add(game_entity)
        self.db_session.commit()
        return game_entity.id

    def find_game(self, game_id: int) -> Game:
        stmt = select(GameEntity).where(GameEntity.id == game_id)
        game_entity = self.db_session.scalars(stmt).one()
        return map_to_game_entity(game_entity)

    def create_player(self, player: Player, game: Game) -> int:
        player_entity = map_to_player_entity(player, game)
        self.db_session.add(player_entity)
        self.db_session.commit()
        return player_entity.id

    def create_vessel(self, vessel: Vessel, battlefield: Battlefield):
        vessel_entity = map_to_vessel_entity(vessel, battlefield)
        self.db_session.add(vessel_entity)
        self.db_session.commit()
        return vessel_entity.id
